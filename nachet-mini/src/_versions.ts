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
  version: "0.10.5",
  name: "nachet-mini",
  versionDate: "2026-05-12T14:47:43.526Z",
};
export default versions;
