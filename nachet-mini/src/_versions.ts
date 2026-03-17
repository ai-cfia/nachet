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
    version: '0.0.6',
    name: 'nachet-mini',
    versionDate: '2026-03-17T23:28:40.932Z',
};
export default versions;
