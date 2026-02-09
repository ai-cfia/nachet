export interface TsAppVersion {
    version: string;
    name: string;
    description?: string;
    versionLong?: string;
    versionDate: string;
    gitCommitHash?: string;
    gitCommitDate?: string;
    gitTag?: string;
};
export const versions: TsAppVersion = {
    version: '2.9.2',
    name: 'nachet-frontend',
    versionDate: '2026-02-09T16:20:00.135Z',
};
export default versions;
