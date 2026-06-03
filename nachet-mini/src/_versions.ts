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
  version: "0.10.10",
  name: "nachet-mini",
  versionDate: "2026-06-03T00:00:00.000Z",
};
export default versions;
