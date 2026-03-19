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
  version: "0.4.0",
  name: "nachet-mini",
  versionDate: "2026-03-19T01:59:21.574Z",
};
export default versions;
