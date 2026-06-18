declare module "oidc-client-ts" {
  export interface UserProfile extends Record<string, unknown> {
    sub?: string;
    name?: string;
    email?: string;
    preferred_username?: string;
  }

  export class User {
    access_token: string;
    profile: UserProfile;
    expired?: boolean;
  }

  export interface SigninRedirectArgs {
    scope?: string;
  }

  export interface SigninSilentArgs {
    scope?: string;
  }

  export interface SignoutRedirectArgs {
    post_logout_redirect_uri?: string;
  }

  export interface UserManagerEvents {
    addUserLoaded(callback: (user: User) => void): () => void;
    addUserUnloaded(callback: () => void): () => void;
    addUserSignedOut(callback: () => void): () => void;
    addSilentRenewError(callback: (error: Error) => void): () => void;
  }

  export interface UserManagerSettings {
    authority: string;
    client_id: string;
    redirect_uri: string;
    post_logout_redirect_uri?: string;
    response_type?: string;
    scope?: string;
    userStore?: unknown;
    automaticSilentRenew?: boolean;
    silent_redirect_uri?: string;
  }

  export class UserManager {
    readonly events: UserManagerEvents;

    constructor(settings: UserManagerSettings);
    getUser(): Promise<User | null>;
    signinCallback(): Promise<User | undefined>;
    signinRedirect(args?: SigninRedirectArgs): Promise<void>;
    signinSilent(args?: SigninSilentArgs): Promise<User | null>;
    signoutRedirect(args?: SignoutRedirectArgs): Promise<void>;
    removeUser(): Promise<void>;
    clearStaleState(): Promise<void>;
  }

  export class WebStorageStateStore {
    constructor(args: { store: Storage });
  }
}
