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
  version: "0.0.1",
  name: "nachet-mini",
  versionDate: "2026-02-19T22:04:05.278Z",
};
export default versions;
