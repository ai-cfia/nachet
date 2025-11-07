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
    version: '2.5.0',
    name: 'nachet-frontend',
    versionDate: '2025-11-07T02:46:40.295Z',
};
export default versions;
