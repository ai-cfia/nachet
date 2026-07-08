export interface TsAppVersion {
  version: string;
  name: string;
  description?: string;
  versionLong?: string;
  versionDate: string;
  gitCommitHash?: string;
  gitCommitDate?: string;
  gitTag?: string;
}
export const versions: TsAppVersion = {
  version: "0.10.15",
  name: "nachet-mini",
  versionDate: "2026-07-14T00:00:00.000Z",
};
export default versions;
