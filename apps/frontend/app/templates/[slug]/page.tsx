import TemplateDetailClient from "./template-detail-client";

export const dynamic = "force-dynamic";

export default function TemplateDetailPage({ params }: { params: { slug: string } }) {
  return <TemplateDetailClient slug={params.slug} />;
}
