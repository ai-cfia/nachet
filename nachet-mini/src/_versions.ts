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
    version: '0.2.3',
    name: 'nachet-mini',
    versionDate: '2026-03-18T18:25:37.735Z',
};
export default versions;
