# Naming Amazon S3 objects

The object key (or key name) uniquely identifies the object in an Amazon S3 bucket. When you create an object, you specify the key name. For example, on the Amazon S3 console, when you select a bucket, a list of objects in your bucket appears. These names are the object keys.

The object key name consists of a sequence of Unicode characters encoded in UTF-8, with a maximum length of 1,024 bytes or approximately 1,024 Latin characters. In some locales, a single character may require 2 bytes for encoding. When naming your objects, be aware of the following:

Object key names are case sensitive.

Object key names include any prefixes (known as folders in the console). For example, Development/Projects.xls is the full object key name of the Projects.xls object located within the Development prefix (or folder). The prefix, the delimiter (/), and the name of the object are included in the 1,024 byte limitation for the object key name. For more information about prefixes and folders, see Choosing object key names.

Certain characters might require special handling when they're used in object key names. For more information, see Object key naming guidelines.

Note
Object key names with the value "soap" aren't supported for virtual-hosted-style requests. For object key name values where "soap" is used, a path-style URL must be used instead.

Choosing object key names

The Amazon S3 data model is a flat structure: You create a bucket, and the bucket stores objects. There is no hierarchy of subbuckets or subfolders. However, you can infer logical hierarchy using key name prefixes and delimiters as the Amazon S3 console does. The Amazon S3 console supports a concept of folders. For more information about how to edit metadata from the Amazon S3 console, see Editing object metadata in the Amazon S3 console.

Suppose that your bucket (admin-created) has four objects with the following object keys:

Development/Projects.xls

Finance/statement1.pdf

Private/taxdocument.pdf

s3-dg.pdf

The console uses the key name prefixes (Development/, Finance/, and Private/) and delimiter (/) to present a folder structure. The s3-dg.pdf key doesn't contain a slash-delimited prefix, so its object appears directly at the root level of the bucket. If you open the Development/ folder, you see the Projects.xlsx object in it.

Amazon S3 supports buckets and objects, and there is no hierarchy. However, by using prefixes and delimiters in an object key name, the Amazon S3 console and the AWS SDKs can infer hierarchy and introduce the concept of folders.

The Amazon S3 console implements folder object creation by creating a zero-byte object with the folder prefix and delimiter value as the key. These folder objects don't appear in the console. Otherwise they behave like any other objects and can be viewed and manipulated through the REST API, AWS CLI, and AWS SDKs.

Object key naming guidelines

You can use any UTF-8 character in an object key name. However, using certain characters in key names can cause problems with some applications and protocols. The following guidelines help you maximize compliance with DNS, web-safe characters, XML parsers, and other APIs.

Safe characters
The following character sets are generally safe for use in key names:

Alphanumeric characters
0-9

a-z

A-Z

Special characters
Exclamation point (!)

Hyphen (-)

Underscore (_)

Period (.)

Asterisk (*)

Single quotation mark (')

Opening parenthesis (()

Closing parenthesis ())

The following are examples of valid object key names:

4my-organization

my.great_photos-2014/jan/myvacation.jpg

videos/2014/birthday/video1.wmv

Note
If you use the Amazon S3 console to download objects that have key names that end with periods (.), the periods are removed from the ends of the key names of the downloaded objects. To retain periods at the ends of key names in downloaded objects, you must use the AWS Command Line Interface (AWS CLI), AWS SDKs, or Amazon S3 REST API.

In addition, be aware of the following prefix limitations:

Objects with a prefix of ./ must be uploaded or downloaded with the AWS CLI, AWS SDKs, or REST API. You can't use the Amazon S3 console to upload these objects.

Object keys that contain relative path elements (for example, ../) are valid if, when parsed left-to-right, the cumulative count of relative path segments never exceeds the number of non-relative path elements encountered. This rule applies to all requests made by using the Amazon S3 console, Amazon S3 REST API, AWS CLI, and AWS SDKs.

For example:

videos/2014/../../video1.wmv is valid.

videos/../../video1.wmv isn't valid.

videos/../../2014/video1.wmv isn't valid.

Period-only path segments
Object keys containing period-only path segments (. or ..) can cause unexpected behavior when processed by applications, SDKs, or tools that interpret these as relative path references.

The following patterns can cause issues:

folder/./file.txt - Contains current directory reference

folder/../file.txt - Contains parent directory reference

./file.txt - Starts with current directory reference

../file.txt - Starts with parent directory reference

The following patterns work normally:

folder/.hidden/file.txt - Period is part of filename, not standalone

folder/..backup/file.txt - Periods are part of filename, not standalone

When applications process object keys with period-only segments, the following behavioral impacts can occur:

Path normalization - Many systems automatically resolve . and .. references, potentially changing the effective path (for example, folder/./file.txt becomes folder/file.txt)

Access issues - Applications might fail to locate objects due to path resolution differences

Inconsistent behavior - Different tools and SDKs might handle these patterns differently

Important
To avoid these issues, we recommend avoiding period-only path segments in object key names. Use alternative naming conventions for organizational purposes.

Characters that might require special handling
The following characters in a key name might require additional code handling and most likely must be URL encoded or referenced as HEX. Some of these characters are non-printable characters that your browser might not handle, which also require special handling:

Ampersand (&)

Dollar sign ($)

ASCII character ranges 00–1F hex (0–31 decimal) and 7F (127 decimal)

At symbol (@)

Equal sign (=)

Semicolon (;)

Forward slash (/)

Colon (:)

Plus sign (+)

Space – Significant sequences of spaces might be lost in some cases (especially multiple spaces)

Comma (,)

Question mark (?)

Characters to avoid
We recommend not using the following characters in a key name because of significant special character handling, which isn't consistent across all applications:

Backslash (\)

Left brace ({)

Non-printable ASCII characters (128–255 decimal characters)

Caret or circumflex (^)

Right brace (})

Percent character (%)

Grave accent or backtick (`)

Right bracket (])

Quotation mark (")

Greater than sign (>)

Left bracket ([)

Tilde (~)

Less than sign (<)

Pound sign (#)

Vertical bar or pipe (|)

XML-related object key constraints
As specified by the XML standard on end-of-line handling, all XML text is normalized such that single carriage returns (ASCII code 13) and carriage returns immediately followed by a line feed (ASCII code 10), also known as newline characters, are replaced by a single line feed character. To ensure the correct parsing of object keys in XML requests, carriage returns and other special characters must be replaced with their equivalent XML entity code when they're inserted within XML tags.

The following is a list of such special characters and their equivalent XML entity codes:

Apostrophe (') must be replaced with &apos;

Quotation mark (") must be replaced with &quot;

Ampersand (&) must be replaced with &amp;

Less than sign (<) must be replaced with &lt;

Greater than sign (>) must be replaced with &gt;

Carriage return (\r) must be replaced with &#13; or &#x0D;

Newline (\n) must be replaced with &#10; or &#x0A;

The following example illustrates the use of an XML entity code as a substitution for a carriage return. This DeleteObjects request deletes an object with the key parameter /some/prefix/objectwith\rcarriagereturn (where the \r is the carriage return).

```xml
<Delete xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <Object>
    <Key>/some/prefix/objectwith&#13;carriagereturn</Key>
  </Object>
</Delete>
```

Object key sort order

Amazon S3 sorts object keys, including prefixes, lexicographically by their UTF-8 encoded byte values.

ASCII characters sort in the following order:

Special characters (for example, !, /)

Uppercase letters (A–Z)

Lowercase letters (a–z)

Non-ASCII characters (for example, é, 中 文) are encoded as multi-byte UTF-8 sequences and typically sort after ASCII characters because of their higher byte values (for example, 0xC3 for é, 0xE4 for 中).

For example, prefixes such as apple/, Apple/, éclair/, 中 文/ would sort as:

1. Apple/ (starts with 0x41)

2. apple/ (starts with 0x61)

3. éclair/ (starts with 0xC3 0xA9)

4. 中 文/ (starts with 0xE4 0xB8 0xAD 0xE6 0x96 0x87)
