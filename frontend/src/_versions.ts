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
    version: '0.13.1',
    name: 'nachet-frontend',
    versionDate: '2025-10-05T21:22:04.211Z',
};
export default versions;
