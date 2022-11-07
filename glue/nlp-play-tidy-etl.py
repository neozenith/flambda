import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrameCollection
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import functions as SqlFuncs

# Script generated for node Clean and Label
def data_clean_and_label(glueContext, dfc) -> DynamicFrameCollection:
    from pyspark.sql import DataFrame
    from pyspark.sql.functions import regexp_replace, lit, udf

    #################################################
    def clean(df: DataFrame) -> DataFrame:
        # Remove balance
        df = df.drop("balance")

        # Remove income and transfers
        df = df.filter(df.amount < 0)

        df = filter_by_prefix(df)
        df = strip_description_noise(df)

        return df

    def filter_by_prefix(df: DataFrame) -> DataFrame:
        # Remove other specific transactions
        prefixes_to_filter = [
            "Transfer",
            "Salary",
            "Direct Credit",
            "Wdl ATM CBA",
            "Home Loan Pymt",
            "Refund Purchase Medicare Benefit",
            "Refund Purchase MEDICARE BENEFIT",
            "Direct Debit 617704 PAYPAL AUSTRALIA",
            "Loan Repayment LN REPAY",
        ]
        for k in prefixes_to_filter:
            df = df.filter(~(df.description.startswith(k)))

        return df

    def strip_description_noise(df: DataFrame) -> DataFrame:
        # Tidy up descriptions
        desc_filters = [
            " Card xx\d\d\d\d",
            " Value Date: \d\d/\d\d/\d\d\d\d",
            " \d\d+",
            "Direct Debit ",
            " AUS",
            " AU",
            " NS",
            " NSWAU",
        ]
        for f in desc_filters:
            df = df.withColumn("description", regexp_replace(df.description, f, ""))

        df = df.withColumn("description", regexp_replace(df.description, "  ", " "))
        return df

    #################################################

    @udf
    def classify_transaction(transaction_description: str):
        output = transaction_description

        # Hard coded rules
        if not transaction_description.startswith("COLES EXPRESS") and any(
            [
                transaction_description.startswith(k)
                for k in [
                    "COLES",
                    "WOOLWORTHS",
                    "RITCHIES SUPA IGA",
                    "THE ESSENTIAL INGRED",
                    "BWS LIQUOR",
                    "HARRIS FARM MARKETS",
                ]
            ]
        ):
            output = "Groceries"
        elif (
            transaction_description.startswith("Loan Repayment LN REPAY")
            or "CommInsure" in transaction_description
        ):
            output = "HomeLoan"
        elif any(
            [
                transaction_description.lower().startswith(k.lower())
                for k in [
                    "COLES EXPRESS",
                    "7-ELEVEN",
                    "BP ",
                    "CALTEX",
                    "METRO PETROLEUM",
                    "SHELL",
                    "AMPOL",
                    "Enhance Neath Service",
                ]
            ]
        ):
            output = "Fuel"
        else:
            output = keyword_classifier(transaction_description)

        # Couldn't classify
        if output == transaction_description:
            output = "Other"

        return output

    def keyword_classifier(transaction_description: str):
        labelled_keywords = {
            "Vehicle": ["Linkt", "CARLOVERS", "SNAP CAR WASH", "TOYOTA", "CIRCUM WASH"],
            "Fitness": [
                "URBANBASEFITNESS",
                "FITNESS PASSPORT",
                "The Forum Univer",
                "THE SELF C*",
                "REBEL",
            ],
            "Utility": ["BPAY"],
            "Health/Pharmacy": [
                "Medical",
                "CHEMIST",
                "PHARMACY",
                "HUMMINGBIRD",
                "COUNSELLIN",
                "DOCS MEGASAVE",
                "Doctors",
                "THE GOOD DENTIST",
                "NOVAHEALTH",
                "PRICELINE",
                "SKINTIFIX",
                "FAMILY MED",
                "WENT PHARM MOSCHAKIS",
                "PLINEPH",
                "PLINE PH",
            ],
            "Parking": ["EASYPARK", "ParkPay", "WESTFIELD"],
            "Newspaper": ["ACM RURAL PRESS"],
            "Cafe": [
                "EQUIUM",
                "ONYX ESPRESSO",
                "HUBRO",
                "KAWUL",
                "BOCADOS",
                "Cafe",
                "T MY ENTERPRISE PL",
                "ALCMARIA PTY LTD",
                "SOUL ORIGIN",
                "AUTUMN ROOMS",
                "KAROO & CO",
            ],
            "Takeaway/Fastfood": [
                "SUSHI",
                "FAHS KITCHEN",
                "OLIVERS",
                "MCDONALDS",
                "Subway",
                "PIE",
                "BAKERS DELIGHT",
            ],
            "Home/Garden/Office": [
                "JB HI",
                "OFFICEWORKS",
                "BUNNINGS",
                "BIG W",
                "TARGET",
                "MISTER MINT",
                "POST",
                "NewsXpress",
            ],
            "Pets/Vet": ["Veterinary"],
        }
        for label, keywords in labelled_keywords.items():
            if any([k.lower() in transaction_description.lower() for k in keywords]):
                return label

        # Not found scenario
        return transaction_description

    def label_transaction(df: DataFrame) -> DataFrame:
        # TODO: Add rules based labelling
        return df.withColumn("rule_based_label", classify_transaction(df.description))

    #################################################

    # https://youtu.be/aEIarW3Ml4c
    # https://youtu.be/tC9UN04a9cU?t=94
    df = dfc.select(list(dfc.keys())[0]).toDF()
    df = clean(df)
    df = label_transaction(df)
    glue_df = DynamicFrame.fromDF(df, glueContext, "data_clean_and_label")
    return DynamicFrameCollection({"default": glue_df}, glueContext)


# Script generated for node conversions
def conversions(glueContext, dfc) -> DynamicFrameCollection:
    from pyspark.sql.functions import to_date
    from pyspark.sql.types import DecimalType

    # https://youtu.be/tC9UN04a9cU?t=94
    df = dfc.select(list(dfc.keys())[0]).toDF()

    df = df.withColumn("tx_date", to_date(df["tx_date"], "d/M/y"))
    df = df.withColumn("amount", df.amount.cast(DecimalType(10, 2)))

    glue_df = DynamicFrame.fromDF(df, glueContext, "transform_date")
    return DynamicFrameCollection({"default": glue_df}, glueContext)


# Script generated for node sagemaker training data format
def convert_training_data(glueContext, dfc) -> DynamicFrameCollection:
    from pyspark.sql.functions import lit

    df = dfc.select(list(dfc.keys())[0]).toDF()

    df = df.drop("tx_date")
    df = df.drop("amount")
    df = df.withColumnRenamed("rule_based_label", "label")
    df = df.withColumnRenamed("description", "source")

    glue_df = DynamicFrame.fromDF(df, glueContext, "training_data")
    return DynamicFrameCollection({"default": glue_df}, glueContext)


args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# Script generated for node Amazon S3
AmazonS3_node1655963788467 = glueContext.create_dynamic_frame.from_catalog(
    database="finances",
    table_name="bronze",
    transformation_ctx="AmazonS3_node1655963788467",
)

# Script generated for node Drop Duplicates
DropDuplicates_node1655965063889 = DynamicFrame.fromDF(
    AmazonS3_node1655963788467.toDF().dropDuplicates(),
    glueContext,
    "DropDuplicates_node1655965063889",
)

# Script generated for node conversions
conversions_node1655991309193 = conversions(
    glueContext,
    DynamicFrameCollection(
        {"DropDuplicates_node1655965063889": DropDuplicates_node1655965063889},
        glueContext,
    ),
)

# Script generated for node Converted From Collection
ConvertedFromCollection_node1656378114683 = SelectFromCollection.apply(
    dfc=conversions_node1655991309193,
    key=list(conversions_node1655991309193.keys())[0],
    transformation_ctx="ConvertedFromCollection_node1656378114683",
)

# Script generated for node Clean and Label
CleanandLabel_node1656374896993 = data_clean_and_label(
    glueContext,
    DynamicFrameCollection(
        {
            "ConvertedFromCollection_node1656378114683": ConvertedFromCollection_node1656378114683
        },
        glueContext,
    ),
)

# Script generated for node Labelled From Collection
LabelledFromCollection_node1655992680099 = SelectFromCollection.apply(
    dfc=CleanandLabel_node1656374896993,
    key=list(CleanandLabel_node1656374896993.keys())[0],
    transformation_ctx="LabelledFromCollection_node1655992680099",
)

# Script generated for node sagemaker training data format
sagemakertrainingdataformat_node1656426965374 = convert_training_data(
    glueContext,
    DynamicFrameCollection(
        {
            "LabelledFromCollection_node1655992680099": LabelledFromCollection_node1655992680099
        },
        glueContext,
    ),
)

# Script generated for node Select From Collection
SelectFromCollection_node1656427244834 = SelectFromCollection.apply(
    dfc=sagemakertrainingdataformat_node1656426965374,
    key=list(sagemakertrainingdataformat_node1656426965374.keys())[0],
    transformation_ctx="SelectFromCollection_node1656427244834",
)

# Script generated for node Amazon S3
AmazonS3_node1656425085899 = glueContext.write_dynamic_frame.from_options(
    frame=ConvertedFromCollection_node1656378114683,
    connection_type="s3",
    format="glueparquet",
    connection_options={
        "path": "s3://play-projects-joshpeak/nlp-play/silver/original/",
        "partitionKeys": [],
    },
    format_options={"compression": "snappy"},
    transformation_ctx="AmazonS3_node1656425085899",
)

# Script generated for node Amazon S3
AmazonS3_node1655963946369 = glueContext.write_dynamic_frame.from_options(
    frame=LabelledFromCollection_node1655992680099,
    connection_type="s3",
    format="glueparquet",
    connection_options={
        "path": "s3://play-projects-joshpeak/nlp-play/silver/labelled/",
        "partitionKeys": [],
    },
    format_options={"compression": "snappy"},
    transformation_ctx="AmazonS3_node1655963946369",
)

# Script generated for node Amazon S3
AmazonS3_node1656427249578 = glueContext.write_dynamic_frame.from_options(
    frame=SelectFromCollection_node1656427244834,
    connection_type="s3",
    format="json",
    connection_options={
        "path": "s3://play-projects-joshpeak/nlp-play/sagemaker/train/",
        "partitionKeys": [],
    },
    transformation_ctx="AmazonS3_node1656427249578",
)

job.commit()
