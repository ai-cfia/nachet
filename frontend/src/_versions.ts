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
    version: '2.0.0',
    name: 'nachet-frontend',
    versionDate: '2025-11-01T20:44:05.637Z',
};
export default versions;
