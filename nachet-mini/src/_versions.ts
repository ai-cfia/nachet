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
  version: "0.3.0",
  name: "nachet-mini",
  versionDate: "2026-03-19T01:30:49.195Z",
};
export default versions;
