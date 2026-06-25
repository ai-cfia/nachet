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
  version: "0.10.11",
  name: "nachet-mini",
  versionDate: "2026-06-25T15:31:10.000Z",
};
export default versions;
