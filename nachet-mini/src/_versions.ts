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
  version: "0.10.1",
  name: "nachet-mini",
  versionDate: "2026-05-05T13:45:43.526Z",
};
export default versions;
