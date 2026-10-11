"""CPU inference using trusted library-object artifacts and caller DataFrames."""
from pathlib import Path
import json

import joblib
import numpy as np
import pandas as pd

from .features import FEATURES, NUMERIC, CATEGORICAL, build_next_day_features


def model_input(frame, features=None):
    features = FEATURES if features is None else features
    result = frame[features].copy()
    if 'season' in result:
        result['season'] = pd.to_numeric(result.season, errors='coerce').astype('Int64').astype('string')
    for c in [c for c in NUMERIC if c in features]:
        result[c] = pd.to_numeric(result[c], errors='raise').replace([np.inf, -np.inf], np.nan).astype('float32')
    for c in [c for c in CATEGORICAL if c in features]:
        result[c] = result[c].astype('string').fillna('__MISSING__').astype(str)
    return result


def catboost_input(frame, preprocessing, *, fit=False, features=None):
    features = FEATURES if features is None else features
    numeric = [c for c in NUMERIC if c in features]
    x = model_input(frame, features)
    for c in numeric:
        x[c + '_missing'] = x[c].isna().astype('float32')
    transform = preprocessing.fit_transform if fit else preprocessing.transform
    x[numeric] = transform(x[numeric]).astype('float32')
    return x


def validate_probabilities(probabilities):
    p = np.asarray(probabilities, dtype=float)
    if p.ndim != 2 or p.shape[1] != 5 or not np.isfinite(p).all():
        raise ValueError('Expected finite probability matrix with five columns')
    if (p < 0).any() or (p > 1).any() or not np.allclose(p.sum(axis=1), 1, atol=1e-6):
        raise ValueError('Probability range or row sums are invalid')
    return p


def predict_probabilities(name, preprocessing, model, metadata, frame):
    if metadata['features'] != FEATURES:
        raise ValueError('Model input contract differs from the active schema')
    x = (catboost_input(frame, preprocessing) if name == 'catboost'
         else preprocessing.transform(model_input(frame)))
    raw = model.predict_proba(x, task_type='CPU') if name == 'catboost' else model.predict_proba(x)
    classes = np.asarray(model.classes_, dtype=int)
    if set(classes) != set(range(5)):
        raise ValueError('Model must contain exactly classes 0..4')
    result = np.zeros((len(frame), 5), dtype=float)
    result[:, classes] = raw
    return validate_probabilities(result)


class FillPredictor:
    def __init__(self, payload, district_aliases):
        self.payload = payload
        self.metadata = payload['metadata']
        self.district_aliases = district_aliases
        if self.metadata['features'] != FEATURES:
            raise ValueError('Incompatible model schema')

    @classmethod
    def load(cls, product_directory):
        directory = Path(product_directory)
        # Load only trusted model files from the delivered package.
        payload = joblib.load(directory / 'model.joblib')
        aliases = json.loads((directory / 'district_aliases.json').read_text(encoding='utf-8'))
        return cls(payload, aliases)

    def predict_proba(self, features):
        return predict_probabilities(self.payload['name'], self.payload['preprocessing'],
                                     self.payload['model'], self.metadata, features)

    def predict_next_day(self, history_df, registry_df, today, day_counters_df=None, population_df=None):
        day = pd.Timestamp(today).normalize() + pd.Timedelta(days=1)
        if pd.Timestamp(self.metadata['train_end']) >= day:
            raise ValueError('Forecast date must follow model fitting')
        features = build_next_day_features(history_df, registry_df, today,
                                          day_counters_df, population_df, self.district_aliases)
        levels = self.predict_proba(features).argmax(axis=1).astype('int8')
        return pd.DataFrame({'bin_id': features.bin_id.to_numpy(), 'fill_level': levels})
