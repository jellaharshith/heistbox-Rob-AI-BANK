import WantedPoster from "@/components/WantedPoster";

export default async function WantedPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <WantedPoster id={decodeURIComponent(id)} />;
}
