import { useTranslation as useT } from "react-i18next";

import ArrowInCircleIcon from "../assets/icons/arrow-in-circle.svg";
import "./AboutPage.css";

function About() {
  const { t } = useT();

  return (
    <div className="home-container">
      <div className="home-section-intro">
        <div className="home-hero">
          <div className="home-content">
            <h1 className="home-title">{t("We break barriers")}</h1>
            <span className="home-caption">
              {t("CREDERE is a financial solution to open opportunities for small businesses in public procurement")}
            </span>
          </div>
        </div>
      </div>

      <div className="home-sections">
        <div className="home-section">
          <div className="home-image" />
          <div className="home-content1">
            <h2 className="home-text01">{t("Why CREDERE?")}</h2>
            <span className="home-text02">
              <span>
                {t(
                  "The public procurement market in Colombia exceeds $150 billion. But almost 70% of small and medium-sized businesses have not obtained external financing from financial institutions, limiting their ability to grow and develop.",
                )}
              </span>
              <br />
              <br />
              <span>
                {t(
                  "This represents a unique opportunity for business growth and the promotion of the country's economic development.",
                )}
              </span>
            </span>
          </div>
        </div>
        <div className="home-section" />
      </div>
      <div className="home-sections1">
        <div className="home-section2">
          <div className="home-image2" />
          <div className="home-content2">
            <h2 className="home-text07">{t("The solution")}</h2>
            <span className="home-text08">
              <span>{t("CREDERE is an innovative tool developed by the Open Contracting Partnership.")}</span>
              <br />
              <br />
              <span>
                {t(
                  "It is the first solution in the region that allows small businesses to gain access to financial products to fulfill public contracts and be more competitive.",
                )}
              </span>
              <br />
            </span>
          </div>
        </div>
        <div className="home-section" />
      </div>
      <div className="home-stats">
        <div className="home-stat">
          <span className="home-caption1">$150</span>
          <span className="home-description">
            <span className="home-text">{t("billions of pesos in annual value of public contracts")}</span>
            <span />
          </span>
        </div>
        <div className="home-stat">
          <span className="home-caption1">78%</span>
          <span className="home-description">
            <span className="home-text">{t("of SMEs has never won a public contract")}</span>
            <span />
          </span>
        </div>
        <div className="home-stat">
          <span className="home-caption1">45%</span>
          <span className="home-description">
            <span className="home-text">{t("cannot assume financial costs")}</span>
            <span />
          </span>
        </div>
        <div className="home-stat">
          <span className="home-caption1">89%</span>
          <span className="home-description">
            <span className="home-text">{t("used informal credits")}</span>
            <span />
            <br />
          </span>
        </div>
      </div>
      <div className="home-features">
        <div className="home-header1">
          <div className="home-tag">
            <span className="home-text25">Noticias</span>
          </div>
          <div className="home-heading1">
            <h2 className="home-text26">CREDERE en las noticias</h2>
          </div>
        </div>
        <div className="home-feature-list">
          <a
            href="https://www.open-contracting.org/es/2023/10/04/credere-llega-a-colombia-para-ayudarle-a-las-pymes-a-contratar-con-el-estado/"
            target="_blank"
            rel="noreferrer noopener"
            className="home-link1"
          >
            <div className="feature-feature home-component01">
              <img alt="ocp-tech" src="/OCP-Credere-invitacion-header.avif" className="feature-image" />
              <div className="feature-content">
                <span className="feature-title">
                  CREDERE llega a Colombia para ayudarle a las Pymes a contratar con el Estado
                </span>
                <span className="feature-description">4 de Octubre 2023</span>
                <span className="feature-description1">Open Contracting Partnership</span>
              </div>
            </div>
          </a>
          <a
            href="https://www.open-contracting.org/2023/06/06/building-financial-solutions-for-small-businesses-in-public-procurement-lessons-from-bogota/"
            target="_blank"
            rel="noreferrer noopener"
            className="home-link1"
          >
            <div className="feature-feature home-component01">
              <img alt="ocp-tech" src="/entrepreneur-woman-1200w.jpeg" className="feature-image" />
              <div className="feature-content">
                <span className="feature-title">
                  Generar soluciones financieras para las pequeñas empresas en la contratación pública: lecciones de
                  Bogotá
                </span>
                <span className="feature-description">6 de Junio 2023</span>
                <span className="feature-description1">Open Contracting Partnership</span>
              </div>
            </div>
          </a>
          <a
            href="https://strivecommunity.org/programs/open-contracting-partnership"
            target="_blank"
            rel="noreferrer noopener"
            className="home-link1"
          >
            <div className="feature-feature home-component01">
              <img alt="ocp-tech" src="/empresaria_domrep-200h.jpg" className="feature-image" />
              <div className="feature-content">
                <span className="feature-title">
                  Open Contracting Partnership: Government contracts made accessible for small businesses
                </span>
                <span className="feature-description">MasterCard Strive Community 2022</span>
              </div>
            </div>
          </a>
        </div>
      </div>
      <br />
      <br />
      <div className="home-sections">
        <div className="home-section">
          <div className="home-container5" />
          <div className="home-content2">
            <h2 className="home-text28">Nuestra historia</h2>
            <span className="home-text29">
              <span>
                En Open Contracting Partnership, estamos convencidos de que los billones invertidos en contratos
                públicos deben contribuir a la construcción de comunidades más equitativas, prósperas y sostenibles.
              </span>
              <br />
              <br />
              <span>
                Este objetivo solo se logra al seleccionar a los proveedores más competentes para cada tarea y al
                asegurar que todas las empresas tengan una oportunidad justa de trabajar con el Estado.
              </span>
              <br />
              <span>
                Esto representa una oportunidad única para el crecimiento empresarial y el fomento del desarrollo
                económico del país.
              </span>
            </span>

            <a
              href="https://www.open-contracting.org/es"
              target="_blank"
              rel="noreferrer noopener"
              className="home-link3"
            >
              <div className="home-ios-btn">
                <img alt="pastedImage" src={ArrowInCircleIcon} className="home-apple" />
                <span className="home-caption5">Aprende más</span>
              </div>
            </a>
            <div className="home-section5" />
          </div>
        </div>
      </div>
      <div className="home-testimonials">
        <div className="home-content4">
          <div id="quotes" className="home-quotes">
            <div className="quote active-quote">
              <div className="quote-quote">
                <div className="quote-quote1">
                  <span className="quote-quote2">
                    &quot;El mercado de compras públicas en Colombia es muy amplio y ofrece una oportunidad única para
                    favorecer el crecimiento empresarial y lograr un mayor desarrollo económico.&quot;
                  </span>
                </div>
                <div className="quote-people">
                  <div className="quote-person">
                    <img alt="person-avatar" src="/credere-oscar-200h.png" className="quote-avatar" />
                    <div className="quote-person-details">
                      <span className="quote-text">Oscar Hernández</span>
                      <span className="">Gerente para América Latina, Open Contracting Partnership</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div />
        </div>
      </div>
      <div className="home-get-started">
        <div className="home-content5">
          <div className="home-heading2">
            <h2 className="home-text38">{t("Do you want to know more?")}</h2>
            <span className="home-text39">
              {t("Are you a financial institution and want to be part of this innovation?")}
            </span>
          </div>
          <div className="home-hero-buttons">
            <a href="mailto:ohernandez@open-contracting.org">
              <div className="home-ios-btn">
                <img alt="pastedImage" src={ArrowInCircleIcon} className="home-apple" />

                <span className="home-caption5">{t("Contact us to join")}</span>
              </div>
            </a>
          </div>
        </div>
      </div>
      <div className="footer-footer">
        <div className="home-content">
          <div className="footer-container">
            <div className="footer-container1">
              <div className="footer-container2">
                <div className="footer-container3">
                  <div className="footer-container4">
                    <img
                      alt="/ocp-credere-brand%20(1)-1500w.png"
                      src="/ocp-credere-brand%20(1)-1500w.png"
                      className="footer-pasted-image"
                    />
                  </div>
                </div>
                <span className="footer-header">Contacto</span>
              </div>
              <p className="footer-text">credere@open-contracting.org</p>
              <p className="footer-text1">Open Contracting Partnership</p>
              <p className="footer-text2">1100 13th Street NW, Suite 800</p>
              <p className="footer-text3">20005, Washington, D.C., USA</p>
            </div>
          </div>
        </div>

        <div className="footer-container5">
          <span className="footer-text5">
            2023. Open Contracting Partnership is an independent non-profit public charity 501(c)(3).
          </span>
          <a
            href="https://www.open-contracting.org/es/about/politica-de-privacidad/"
            target="_blank"
            rel="noreferrer noopener"
            className="footer-link"
          >
            Privacidad
          </a>
        </div>
      </div>
    </div>
  );
}
export default About;
