import HealthStatus from "./HealthStatus";
import PolicyCompiler from "./PolicyCompiler";
import TwinWorkspace from "../components/twin/TwinWorkspace";
import ParliamentPanel from "../components/twin/ParliamentPanel";
import FailureModesPanel from "../components/twin/FailureModesPanel";
import PublicReactionPanel from "../components/twin/PublicReactionPanel";
import { TwinProvider } from "../components/twin/TwinStore";

export default function Home() {
  return (
    <main>
      <p className="eyebrow">URBAN · Policy Digital Twin</p>
      <h1>Simulate the city before you change it.</h1>
      <p className="lede">
        Draft a policy in plain language, then watch two worlds diverge — a
        baseline city and one where the policy takes effect — across traffic,
        emissions, transit demand, equity and public support. Every number is
        tagged <strong>Observed</strong>, <strong>Estimated</strong>,{" "}
        <strong>Simulated</strong> or <strong>Generated</strong>, and long-run
        uncertainty widens honestly.
      </p>

      <TwinProvider>
        <PolicyCompiler />

        <TwinWorkspace />

        <ParliamentPanel />

        <PublicReactionPanel />

        <FailureModesPanel />
      </TwinProvider>

      <HealthStatus />

      <p className="hint">
        Demo policy: pedestrianise / price vehicles entering a central district
        and reinvest the revenue into public transport.
      </p>
    </main>
  );
}
