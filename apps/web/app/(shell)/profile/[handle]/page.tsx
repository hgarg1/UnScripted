import { ProfileView } from "../../../../components/views";

export default async function PublicProfilePage({
  params,
}: {
  params: Promise<{ handle: string }>;
}) {
  const { handle } = await params;
  return <ProfileView handle={handle} />;
}
