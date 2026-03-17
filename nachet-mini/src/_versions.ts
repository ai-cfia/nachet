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
    version: '0.0.3',
    name: 'nachet-mini',
    versionDate: '2026-03-17T21:14:08.784Z',
};
export default versions;
