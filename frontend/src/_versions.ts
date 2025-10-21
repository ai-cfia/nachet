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
    version: '0.16.0',
    name: 'nachet-frontend',
    versionDate: '2025-10-20T22:42:21.846Z',
};
export default versions;
