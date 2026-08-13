import CityStudio from "../components/city/CityStudio";
import AdvancedTwin from "../components/twin/AdvancedTwin";
import { TwinProvider } from "../components/twin/TwinStore";

export default function Home() {
  return (
    <main className="wide">
      <p className="eyebrow">URBAN · Policy Digital Twin</p>
      <h1>Drag ten years. Watch the city change.</h1>
      <p className="lede">
        Meridia is a prebuilt 3D city. Pick a policy, then scrub the decade:
        traffic thins, buildings rise where transit is funded, and central
        kerbside turns into public realm. The projection is a mechanistic model
        run over an origin–destination commute matrix — tagged{" "}
        <strong>Simulated</strong>, never presented as fact, and never produced
        by a language model.
      </p>

      <CityStudio />

      <TwinProvider>
        <AdvancedTwin />
      </TwinProvider>
    </main>
  );
}
