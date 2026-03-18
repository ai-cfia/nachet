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
    version: '0.2.2',
    name: 'nachet-mini',
    versionDate: '2026-03-18T16:14:54.653Z',
};
export default versions;
