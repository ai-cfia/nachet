# Naming and Referencing Containers, Blobs, and Metadata

10/10/2023
This topic describes naming and referring to containers, blobs, metadata, and snapshots. A storage account can contain zero or more containers. A container contains properties, metadata, and zero or more blobs. If your account has a hierarchical namespace, then a container can also contain zero or more directories and those directories can contain zero or more blobs. A blob is any single entity comprised of binary data, properties, and metadata.

Resource Names
The URI to reference a container or a blob must be unique. Because every account name is unique, two accounts can have containers with the same name. However, within a given storage account, every container must have a unique name. Every blob within a given container must also have a unique name within that container.

If you attempt to create a container or blob with a name that violates naming rules, the request will fail with status code 400 (Bad Request).

Blob and container names are passed to the Blob service within a URL. Certain characters must be percent-encoded to appear in a URL, using UTF-8 (preferred) or MBCS. This encoding occurs automatically when you use the Azure Storage client libraries. However, there are certain characters that are not valid in URL paths even when encoded. If these characters appear in blob or container names, the request may fail. For a list of these characters, see Unicode characters not recommended for use in container or blob names.

Code points like \uE000, while valid in NTFS filenames, are not valid Unicode characters, so they cannot be used. In addition, some ASCII or Unicode characters, like control characters (0x00 to 0x1F, \u0081, etc.), are also not allowed.

For additional rules governing Unicode strings in HTTP/1.1, see RFC 2616, Section 2.2: Basic Rules and RFC 3987.

Container Names
A container name must be a valid DNS name, conforming to the following naming rules:

Container names must start or end with a letter or number, and can contain only letters, numbers, and the hyphen/minus (-) character.

Every hyphen/minus (-) character must be immediately preceded and followed by a letter or number; consecutive hyphens aren't permitted in container names.

All letters in a container name must be lowercase.

Container names must be from 3 through 63 characters long.

Directory names
If your account has a hierarchical namespace, then a directory name must conform to the following naming rules:

A directory name can contain any combination of characters.

A directory name must be at least one character long and cannot be more than 1,024 characters long.

Directory names are case-sensitive.

Reserved URL characters must be properly escaped.

 Note

Avoid directory names that end with a dot (.), a forward slash (/), a backslash (\), or a sequence or combination of the two. No path segments should end with a dot (.).

Screenshot of backslash not allowed.

Blob Names
A blob name must conform to the following naming rules. These rules apply also to blobs in accounts that have a hierarchical namespace, unless otherwise noted.

A blob name can contain any combination of characters.

A blob name must be at least one character long and cannot be more than 1,024 characters long, for blobs in Azure Storage.

The Azure Storage emulator supports blob names up to 256 characters long. For more information, see Use the Azure storage emulator for development and testing.

Blob names are case-sensitive.

Reserved URL characters must be properly escaped.

There are limitations on the number of path segments comprising a blob name. A path segment is the string between consecutive delimiter characters (for example, a forward slash /) that corresponds to the directory or virtual directory. The following path segment limitations apply to blob names:

If the storage account does not have hierarchical namespace enabled, the number of path segments comprising the blob name cannot exceed 254.
If the storage account has hierarchical namespace enabled, the number of path segments comprising the blob name cannot exceed 63 (including path segments for account name and container name).
 Note

Avoid blob names that end with a dot (.), a forward slash (/), a backslash (\), or a sequence or combination of the two. No path segments should end with a dot (.).

Screenshot of forward slash not allowed.

By default, the Blob service is based on a flat storage scheme, not a hierarchical scheme. However, you may specify a character or string delimiter within a blob name to create a virtual hierarchy. For example, the following list shows valid and unique blob names. Notice that a string can be valid as both a blob name and as a virtual directory name in the same container:

/a

/a.txt

/a/b

/a/b.txt

You can take advantage of the delimiter character when enumerating blobs.

Metadata Key and Value Names
Metadata for a container or blob resource is stored as name-value pairs associated with the resource. Metadata key names must adhere to the following naming rules:

Must start with a letter or underscore

Any following characters may be letters, numbers, or underscores

Metadata key name must be valid ASCII

Metadata value names must also be valid ASCII. Note that metadata names preserve the case with which they were created, but are case-insensitive when set or read. If two or more metadata headers with the same name are submitted for a resource, the Blob service returns status code 400 (Bad Request).

Resource URI Syntax
Each resource has a corresponding base URI, which refers to the resource itself.

For the storage account, the base URI includes the name of the account only:

<https://myaccount.blob.core.windows.net>

For a container, the base URI includes the name of the account and the name of the container:

<https://myaccount.blob.core.windows.net/mycontainer>

For a blob, the base URI includes the name of the account, the name of the container, and the name of the blob:

<https://myaccount.blob.core.windows.net/mycontainer/myblob>

A storage account may have a root container, a default container that can be omitted from the URI. A blob in the root container can be referenced without naming the container, or the root container can be explicitly referenced by its name ($root). See Working with the Root Container for more information. The following URIs both refer to a blob in the root container:

Copy
<https://myaccount.blob.core.windows.net/myblob>  
<https://myaccount.blob.core.windows.net/$root/myblob>  
Blob Snapshots
A snapshot is a read-only version of a blob stored as it was at the time the snapshot was created. You can use snapshots to create a backup or checkpoint of a blob. A snapshot blob name includes the base blob URI plus a date-time value that indicates when the snapshot was created.

For example, assume that a blob has the following URI:

<https://myaccount.blob.core.windows.net/mycontainer/myblob>

The URI for a snapshot of that blob is formed as follows:

```text
<https://myaccount.blob.core.windows.net/mycontainer/myblob?snapshot=><DateTime>
```

Unicode characters not recommended for use in container or blob names
The following table provides a list of Unicode characters that are not recommended for use in container or blob names. These characters, when used in combination with other characters in this list, may fail UTF-8 or MBCS decoding, leading to failure of the request to the Blob service.

Unicode character
U+0080
U+0082
U+0083
U+0084
U+0085
U+0086
U+0087
U+0088
U+0089
U+008A
U+008B
U+008C
U+008E
U+0091
U+0092
U+0093
U+0094
U+0095
U+0096
U+0097
U+0098
U+0099
U+009A
U+009B
U+009C
U+009E
U+009F
U+FDD1
U+FDD2
U+FDD3
U+FDD4
U+FDD5
U+FDD6
U+FDD7
U+FDD8
U+FDD9
U+FDDA
U+FDDB
U+FDDC
U+FDDE
U+FDDF
U+FDE0
U+FDE1
U+FDE2
U+FDE3
U+FDE4
U+FDE5
U+FDE6
U+FDE7
U+FDE8
U+FDE9
U+FDEA
U+FDEB
U+FDEC
U+FDED
U+FDEE
U+FDEF
U+FFF0
U+FFF1
U+FFF2
U+FFF3
U+FFF4
U+FFF5
U+FFF6
U+FFF7
U+FFF8
U+FFF9
U+FFFA
U+FFFB
U+FFFC
U+FFFD
U+FFFE
U+FFFF
U+1FFFE
U+1FFFF
U+2FFFE
U+2FFFF
U+3FFFE
U+3FFFF
U+5FFFE
U+5FFFF
U+6FFFE
U+6FFFF
U+7FFFE
U+7FFFF
U+9FFFE
U+9FFFF
U+AFFFE
U+AFFFF
U+BFFFE
U+BFFFF
U+DFFFE
U+DFFFF
U+EFFFE
U+EFFFF
U+FFFFE
U+FFFFF
