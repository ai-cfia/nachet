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
    version: '0.0.2',
    name: 'nachet-mini',
    versionDate: '2026-03-17T18:15:26.260Z',
};
export default versions;
