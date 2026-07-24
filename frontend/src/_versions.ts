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
    version: '3.0.4',
    name: 'nachet-frontend',
    versionDate: '2026-07-24T21:30:41.000Z',
};
export default versions;
