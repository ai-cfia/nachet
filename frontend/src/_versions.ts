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
    version: '2.7.0',
    name: 'nachet-frontend',
    versionDate: '2025-11-26T17:55:14.901Z',
};
export default versions;
