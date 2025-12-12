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
    version: '2.8.0',
    name: 'nachet-frontend',
    versionDate: '2025-12-12T14:36:17.959Z',
};
export default versions;
