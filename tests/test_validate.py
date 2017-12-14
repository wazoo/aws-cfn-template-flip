"""                                                                                                      
Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                  
                                                                                                         
Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at                                              
                                                                                                         
    http://aws.amazon.com/apache2.0/                                                                     
                                                                                                         
or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.                                                 
"""

import pytest
from cfn_clean.validate import validate, ValidationError


@pytest.fixture
def valid_input():
    return {
        "Resources": {
            "Bucket": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": "mr-bucket",
                },
            },
        },
    }


def test_valid(valid_input):
    """
    Test that valid data passes ok
    """

    assert validate(valid_input)


def test_bad_data():
    """
    Test we fail on invalid data type
    """

    with pytest.raises(ValidationError, message="Badly formatted input"):
        validate("This should be a dict")


def test_missing_resources():
    """
    Test we fail on missing resources
    """

    with pytest.raises(ValidationError, message="Missing \"Resources\" property"):
        validate({})


def test_bad_resource():
    """
    Test we fail on a badly-formatted resource
    """

    source = {
        "Resources": {
            "Test": {},
        },
    }

    with pytest.raises(ValidationError, message="Badly formatted resource: Test"):
        validate(source)


def test_invalid_resource_type():
    """
    Test we fail on missing resources
    """

    source = {
        "Resources": {
            "Test": {
                "Type": "AWS::Cutlery::Spoon",
            },
        },
    }

    with pytest.raises(ValidationError, message="Resource \"Test\" has invalid type: AWS::Cutlery::Spoon"):
        validate(source)


def test_missing_properties():
    """
    Test for missing properties
    """

    source = {
        "Resources": {
            "Test": {
                "Type": "AWS::EC2::Instance",
            },
        },
    }

    with pytest.raises(ValidationError, message="Resource \"Test\" has missing required properties: ImageId"):
        validate(source)


def test_unexpected_properties():
    """
    Test for missing properties
    """

    source = {
        "Resources": {
            "Test": {
                "Type": "AWS::EC2::Instance",
                "Properties": {
                    "ImageId": "GladOS-0.1",
                    "Cake": "lie",
                    "WeightInKilograms": 10,
                },
            },
        },
    }

    with pytest.raises(ValidationError, message="Resource \"Test\" has unexpected properties: Cake, WeightInKilograms"):
        validate(source)


def test_wrong_type():
    """
    Check we fail when we receive an unexpected type
    """

    source = {
        "Resources": {
            "Test": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": 10,
                },
            },
        },
    }

    with pytest.raises(ValidationError, message="Resource \"Test\" has invalid data in property \"BucketName\": 10 \(String expected\)"):
        validate(source)


def test_custom_type():
    """
    Validation should check for custom types
    """

    source = {
        "Resources": {
            "Test": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": "Fred",
                    "VersioningConfiguration": {
                        "Status": 10  # This is supposed to be a string
                    },
                },
            },
        },
    }

    with pytest.raises(ValidationError, message="Resource \"Test\" has invalid data in property \"Status\": 10 \(String expected\)"):
        validate(source)


def test_get_att():
    """
    Validation should check for GetAtt
    """

    source = {
        "Resources": {
            "First": {
                "Type": "AWS::S3::Bucket",
            },
            "Test": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "BucketName": {
                        "Fn::GetAtt": ["First", "DomainName"],
                    },
                },
            },
        },
    }

    validate(source)  # No error here


def test_bad_get_att():
    """
    Validation should fail for GetAtt that returns the wrong type
    """

    source = {
        "Resources": {
            "First": {
                "Type": "AWS::S3::Bucket",
            },
            "Test": {
                "Type": "AWS::S3::Bucket",
                "Properties": {
                    "CorsConfiguration": {
                        "Fn::GetAtt": ["First", "DomainName"],
                    },
                },
            },
        },
    }

    with pytest.raises(ValidationError, message="Resource \"Test\" has invalid data in property \"CorsConfiguration\". \(GetAtt returns wrong data type\)"):
        validate(source)
