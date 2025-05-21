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
    version: '0.9.4',
    name: 'nachet-frontend',
    versionDate: '2024-10-25T00:10:51.072Z',
    gitCommitHash: '6fb11aa',
    versionLong: '0.9.4-6fb11aa',
};
export default versions;
