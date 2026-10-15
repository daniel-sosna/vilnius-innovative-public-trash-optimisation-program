import { WolfMascot } from '@/brand/wolf-mascot'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { VipTopLogo } from '@/components/viptop-logo'
import { VilniusLogo } from '@/components/vilnius-logo'

export function RoleSelection() {
  return (
    <main className="mx-auto flex min-h-dvh max-w-md flex-col px-6 pt-8 pb-12 sm:pt-14">
      <div className="flex justify-center">
        <VilniusLogo />
      </div>
      <div className="flex flex-1 flex-col justify-center gap-8 py-8">
        <div className="text-center">
          <div className="mb-6 flex justify-center">
            <VipTopLogo />
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">
            Pasirinkite vaidmenį
          </h1>
        </div>
        <WolfMascot size={240} className="mx-auto" />
        <div className="flex flex-col gap-3">
          <Button variant="outline" size="lg" asChild>
            <Link to="/driver">Vairuotojas</Link>
          </Button>
          <Button size="lg" asChild>
            <Link to="/admin/trucks">Administratorius</Link>
          </Button>
        </div>
      </div>
    </main>
  )
}
