import { BackendRouterSection } from "@/components/vidiolingua/backend-router-section";
import { DemoShowcase } from "@/components/vidiolingua/demo-showcase";
import { LanguageSupportSection } from "@/components/vidiolingua/language-support-section";
import { OttDeliverySection } from "@/components/vidiolingua/ott-delivery-section";
import { QualitySection } from "@/components/vidiolingua/quality-section";
import { SiteFooter } from "@/components/vidiolingua/site-footer";
import { SiteNavigation } from "@/components/vidiolingua/site-navigation";
import { VideoLinguaCtaSection } from "@/components/vidiolingua/cta-section";
import { VideoLinguaHeroSection } from "@/components/vidiolingua/hero-section";
import { WorkflowSection } from "@/components/vidiolingua/workflow-section";

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-x-hidden noise-overlay">
      <SiteNavigation />
      <VideoLinguaHeroSection />
      <DemoShowcase />
      <WorkflowSection />
      <BackendRouterSection />
      <OttDeliverySection />
      <LanguageSupportSection />
      <QualitySection />
      <VideoLinguaCtaSection />
      <SiteFooter />
    </main>
  );
}
