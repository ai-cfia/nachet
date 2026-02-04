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
    version: '2.9.1',
    name: 'nachet-frontend',
    versionDate: '2026-01-30T17:33:23.729Z',
};
export default versions;
