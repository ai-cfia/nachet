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
    version: '0.2.0',
    name: 'nachet-mini',
    versionDate: '2026-03-18T02:11:47.371Z',
};
export default versions;
