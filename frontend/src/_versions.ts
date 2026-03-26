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
    version: '2.9.7',
    name: 'nachet-frontend',
    versionDate: '2026-03-26T20:40:12.059Z',
};
export default versions;
