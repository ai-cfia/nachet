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
  version: "0.10.7",
  name: "nachet-mini",
  versionDate: "2026-05-28T15:18:37.000Z",
};
export default versions;
