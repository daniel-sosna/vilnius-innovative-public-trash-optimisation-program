# Design

## Context

Service zones use the shared polygon renderer with a light teal fill below population and outlines/names above the other polygon areas. The user revised the request to remove crosshatching and make the borders bolder, and explicitly requested no verification.

## Goals / Non-Goals

**Goals:** Clearly distinguish zone boundaries with minimal styling changes.

**Non-Goals:** Pattern rendering, new geometry, changes to labels or interactions, backend changes and data imports.

## Decisions

Restore the original teal fill at opacity 0.15 and area order 15. Increase the dark teal outline width from 1.5 to 3.5, retaining outline/name order 30 so the boundary remains above population and district colors and below point markers. Remove the pattern generator and the shared renderer's newly introduced pattern-image support.

## Risks / Trade-offs

The thicker outline makes boundaries clearer while retaining the existing area colors. Final visual assessment belongs to the user; no additional checks are to be run.

## Migration Plan

The running development frontend serves the styling edit. Refresh the analytics page to inspect it. No database migration or re-import is required.
