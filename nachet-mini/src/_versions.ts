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
  version: "0.5.0",
  name: "nachet-mini",
  versionDate: "2026-03-19T04:30:25.619Z",
};
export default versions;
