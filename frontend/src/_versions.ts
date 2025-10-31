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
    version: '0.18.0',
    name: 'nachet-frontend',
    versionDate: '2025-10-31T02:02:19.791Z',
};
export default versions;
