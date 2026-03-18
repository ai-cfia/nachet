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
    version: '0.2.5',
    name: 'nachet-mini',
    versionDate: '2026-03-18T22:29:50.461Z',
};
export default versions;
