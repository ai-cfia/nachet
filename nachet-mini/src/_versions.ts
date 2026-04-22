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
  version: "0.9.5",
  name: "nachet-mini",
  versionDate: "2026-04-22T13:45:43.526Z",
};
export default versions;
