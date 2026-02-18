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
    version: '2.9.3',
    name: 'nachet-frontend',
    versionDate: '2026-02-13T17:30:06.565Z',
};
export default versions;
