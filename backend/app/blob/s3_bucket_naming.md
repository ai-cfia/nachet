# General purpose bucket naming rules

When you create a general purpose bucket, make sure that you consider the length, valid characters, formatting, and uniqueness of bucket names. The following sections provide information about general purpose bucket naming, including naming rules, best practices, and an example for creating a general purpose bucket with a name that includes a globally unique identifier (GUID).

For information about object key names, see Creating object key names.

To create a general purpose bucket, see Creating a general purpose bucket.

Topics
General purpose buckets naming rules

Example general purpose bucket names

Best practices

Creating a bucket that uses a GUID in the bucket name

General purpose buckets naming rules

The following naming rules apply for general purpose buckets.

Bucket names must be between 3 (min) and 63 (max) characters long.

Bucket names can consist only of lowercase letters, numbers, periods (.), and hyphens (-).

Bucket names must begin and end with a letter or number.

Bucket names must not contain two adjacent periods.

Bucket names must not be formatted as an IP address (for example, 192.168.5.4).

Bucket names must not start with the prefix xn--.

Bucket names must not start with the prefix sthree-.

Bucket names must not start with the prefix amzn-s3-demo-.

Bucket names must not end with the suffix -s3alias. This suffix is reserved for access point alias names. For more information, see Access point aliases.

Bucket names must not end with the suffix --ol-s3. This suffix is reserved for Object Lambda Access Point alias names. For more information, see How to use a bucket-style alias for your S3 bucket Object Lambda Access Point.

Bucket names must not end with the suffix .mrap. This suffix is reserved for Multi-Region Access Point names. For more information, see Rules for naming Amazon S3 Multi-Region Access Points.

Bucket names must not end with the suffix --x-s3. This suffix is reserved for directory buckets. For more information, see Directory bucket naming rules.

Bucket names must not end with the suffix --table-s3. This suffix is reserved for S3 Tables buckets. For more information, see Amazon S3 table bucket, table, and namespace naming rules.

Buckets used with Amazon S3 Transfer Acceleration can't have periods (.) in their names. For more information about Transfer Acceleration, see Configuring fast, secure file transfers using Amazon S3 Transfer Acceleration.

Important
Bucket names must be unique across all AWS accounts in all of the AWS Regions within a partition. A partition is a grouping of Regions. AWS currently has three partitions: aws (commercial Regions), aws-cn (China Regions), and aws-us-gov (AWS GovCloud (US) Regions).

A bucket name can't be used by another AWS account in the same partition until the bucket is deleted. After you delete a bucket, be aware that another AWS account in the same partition can use the same bucket name for a new bucket and can therefore potentially receive requests intended for the deleted bucket. If you want to prevent this, or if you want to continue to use the same bucket name, don't delete the bucket. We recommend that you empty the bucket and keep it, and instead, block any bucket requests as needed. For buckets no longer in active use, we recommend emptying the bucket of all objects to minimize costs while retaining the bucket itself.

When you create a general purpose bucket, you choose its name and the AWS Region to create it in. After you create a general purpose bucket, you can't change its name or Region.

Don't include sensitive information in the bucket name. The bucket name is visible in the URLs that point to the objects in the bucket.

Note
Before March 1, 2018, buckets created in the US East (N. Virginia) Region could have names that were up to 255 characters long and included uppercase letters and underscores. Beginning March 1, 2018, new buckets in US East (N. Virginia) must conform to the same rules applied in all other Regions.

Example general purpose bucket names

The following bucket names show examples of which characters are allowed in general purpose bucket names: a-z, 0-9, and hyphens (-). The amzn-s3-demo- reserved prefix is used here only for illustration. Because it's a reserved prefix, you can't create bucket names that start with amzn-s3-demo-.

amzn-s3-demo-bucket1-a1b2c3d4-5678-90ab-cdef-example11111

amzn-s3-demo-bucket

The following example bucket names are valid but not recommended for uses other than static website hosting because they contain periods (.):

example.com  <!-- markdownlint-disable-line MD034 -->

<www.example.com>  <!-- markdownlint-disable-line MD034 -->

my.example.s3.bucket

The following example bucket names are not valid:

amzn_s3_demo_bucket (contains underscores)

AmznS3DemoBucket (contains uppercase letters)

amzn-s3-demo-bucket- (starts with amzn-s3-demo- prefix and ends with a hyphen)

example..com (contains two periods in a row)

192.168.5.4 (matches format of an IP address)

Best practices

When naming your general purpose buckets, consider the following bucket naming best practices.

Choose a bucket naming scheme that's unlikely to cause naming conflicts
If your application automatically creates buckets, choose a bucket naming scheme that's unlikely to cause naming conflicts. Ensure that your application logic will choose a different bucket name if a bucket name is already taken.

Append globally unique identifiers (GUIDs) to bucket names
We recommend that you create bucket names that aren't predictable. Don't write code assuming your chosen bucket name is available unless you have already created the bucket. One method for creating bucket names that aren't predictable is to append a Globally Unique Identifier (GUID) to your bucket name, for example, amzn-s3-demo-bucket-a1b2c3d4-5678-90ab-cdef-example11111. For more information, see Creating a bucket that uses a GUID in the bucket name.

Avoid using periods (.) in bucket names
For best compatibility, we recommend that you avoid using periods (.) in bucket names, except for buckets that are used only for static website hosting. If you include periods in a bucket's name, you can't use virtual-host-style addressing over HTTPS, unless you perform your own certificate validation. The security certificates used for virtual hosting of buckets don't work for buckets with periods in their names.

This limitation doesn't affect buckets used for static website hosting, because static website hosting is available only over HTTP. For more information about virtual-host-style addressing, see Virtual hosting of general purpose buckets. For more information about static website hosting, see Hosting a static website using Amazon S3.

Choose a relevant name
When you name a bucket, we recommend that you choose a name that's relevant to you or your business. Avoid using names associated with others. For example, avoid using AWS or Amazon in your bucket name.

Don't delete buckets so that you can reuse bucket names
If a bucket is empty, you can delete it. After a bucket is deleted, the name becomes available for reuse. However, you aren't guaranteed to be able to reuse the name right away, or at all. After you delete a bucket, some time might pass before you can reuse the name. In addition, another AWS account might create a bucket with the same name before you can reuse the name.

After you delete a general purpose bucket, be aware that another AWS account in the same partition can use the same bucket name for a new bucket and can therefore potentially receive requests intended for the deleted general purpose bucket. If you want to prevent this, or if you want to continue to use the same general purpose bucket name, don't delete the general purpose bucket. We recommend that you empty the bucket and keep it, and instead, block any bucket requests as needed.
