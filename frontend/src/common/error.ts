class DecodeError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "DecodeError";
  }
}

class FetchError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "FetchError";
  }
}

class BlobError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "BlobError";
  }
}

class AzureAPIError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "AzureAPIError";
  }
}

class ValueError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ValueError";
  }
}

class UploadError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "UploadError";
  }
}

export {
  DecodeError,
  FetchError,
  BlobError,
  AzureAPIError,
  ValueError,
  UploadError,
};
