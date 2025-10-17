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
    version: '0.14.0',
    name: 'nachet-frontend',
    versionDate: '2025-10-17T06:07:34.008Z',
};
export default versions;
