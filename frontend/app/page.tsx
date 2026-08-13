import CityStudio from "../components/city/CityStudio";
import HeroVisual from "../components/city/HeroVisual";
import Reveal from "../components/Reveal";
import AdvancedTwin from "../components/twin/AdvancedTwin";
import FeatureShowcase from "../components/twin/FeatureShowcase";
import { TwinProvider } from "../components/twin/TwinStore";

export default function Home() {
  return (
    <main className="wide">
      <header className="site-header">
        <span className="wordmark">URBAN</span>
        <span className="site-header-sub">Policy Digital Twin</span>
      </header>

      <section className="hero">
        <HeroVisual />
        <div className="hero-grid-bg" aria-hidden />
        <div className="hero-main">
          <p className="eyebrow">Meridia · Synthetic city, 10-year horizon</p>
          <h1>
            Drag ten years. <em>Watch the city change.</em>
          </h1>
          <p className="lede">
            Meridia is a prebuilt 3D city. Pick a policy, then scrub the decade:
            traffic thins, buildings rise where transit is funded, and central
            kerbside turns into public realm. The projection is a mechanistic
            model run over an origin–destination commute matrix — tagged{" "}
            <strong>Simulated</strong>, never presented as fact, and never
            produced by a language model.
          </p>
          <div className="hero-ctas">
            <a className="btn primary" href="#meridia">
              Explore Meridia
            </a>
            <a className="btn" href="#advanced">
              Open the full twin
            </a>
          </div>
        </div>

        <aside className="title-block" aria-label="Instrument details">
          <div className="title-block-row title-block-head">
            <span>Project</span>
            <strong>Meridia</strong>
          </div>
          <div className="title-block-row">
            <span>Instrument</span>
            <strong>Digital twin</strong>
          </div>
          <div className="title-block-row">
            <span>Projection</span>
            <strong>Cordon demand model</strong>
          </div>
          <div className="title-block-row">
            <span>Scale</span>
            <strong>1 : 10 yr</strong>
          </div>
          <div className="title-block-legend">
            <span className="tag observed">Observed</span>
            <span className="tag estimated">Estimated</span>
            <span className="tag simulated">Simulated</span>
            <span className="tag generated">Generated</span>
          </div>
        </aside>
      </section>

      <Reveal>
        <CityStudio />
      </Reveal>

      <Reveal>
        <FeatureShowcase />
      </Reveal>

      <TwinProvider>
        <Reveal>
          <AdvancedTwin />
        </Reveal>
      </TwinProvider>
    </main>
  );
}
