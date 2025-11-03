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
    version: '2.1.0',
    name: 'nachet-frontend',
    versionDate: '2025-11-03T03:16:21.180Z',
};
export default versions;
