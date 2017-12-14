"""                                                                                                      
Copyright 2016 Amazon.com, Inc. or its affiliates. All Rights Reserved.                                  
                                                                                                         
Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at                                              
                                                                                                         
    http://aws.amazon.com/apache2.0/                                                                     
                                                                                                         
or in the "license" file accompanying this file. This file is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.                                                 
"""

import json
import os
import sys

SPEC_FILE = os.path.join(os.path.dirname(__file__), "../resources/CloudFormationResourceSpecification.json")


# Where we can't be certain of the type of a value
# we give it the benefit of the doubt
MAGIC_TYPE = "Benefit of the doubt"
STRING_TYPE = "String"
BOOLEAN_TYPE = "Boolean"
JSON_TYPE = "Json"
LIST_TYPE = "List"
NUMBER_TYPE = ("Double", "Float", "Integer")

FN_TYPE_MAP = {
    "Fn::Base64": STRING_TYPE,
    "Fn::If": lambda value, source: get_value_type(value[1]),
    "Fn::FindInMap": lambda value, source: get_value_type(source["Mappings"][value[0]][value[1]][value[2]]),
    "Fn::GetAZs": (LIST_TYPE, STRING_TYPE),
    "Fn::ImportValue":  MAGIC_TYPE,
    "Fn::Join": STRING_TYPE,
    "Fn::Select": MAGIC_TYPE,
    "Fn::Sub": STRING_TYPE,
    "Ref": MAGIC_TYPE  # TODO: Look up parameters
}

class ValidationError(Exception):
    pass

with open(os.path.join(os.path.dirname(__file__), SPEC_FILE), "r") as f:
    SPEC = json.load(f)

def get_value_type(value, source=None):
    """
    Returns the value's type taking Refs, Joins, and GetAtts into account
    """

    if isinstance(value, dict):
        if len(value.keys()) > 1 :
            return JSON_TYPE

        fn_name = list(value.keys())[0]

        value_type = FN_TYPE_MAP.get(fn_name, JSON_TYPE)

        if callable(value_type):
            value_type = value_type(value[fn_name], source)

        return value_type

    if isinstance(value, list):
        return (LIST_TYPE, get_value_type(value[0]))

    if isinstance(value, str):
        return STRING_TYPE

    if isinstance(value, bool):
        return BOOLEAN_TYPE

    if isinstance(value, int) or isinstance(value, float):
        return NUMBER_TYPE

    raise ValidationError("WTF:", value)

def validate_ref(ref_name, source):
    """
    Confirm that the specified ref is valid
    """

    return True

def get_att_spec(value, source):
    """
    Confirm that the specificied resource has the attribute in question
    """

    resource = source["Resources"][value[0]]

    resource_type = resource["Type"]

    attribute_spec = SPEC["ResourceTypes"][resource_type].get("Attributes", {}).get(value[1])

    return attribute_spec

def validate_property(resource_name, property_name, value, spec, source):
    """
    Compare the specified value against the supplied spec.
    The entire source must be passed in to ensure that references etc are valid
    """

    def fail(expected_type):
        raise ValidationError("Resource \"{}\" has invalid data in property \"{}\": {} ({} expected)".format(resource_name, property_name, value, expected_type))

    if isinstance(value, dict) and "Fn::GetAtt" in value:
        att_spec = get_att_spec(value["Fn::GetAtt"], source)

        att_type = "{}/{}/{}/{}".format(
            att_spec.get("Type", ""),
            att_spec.get("PrimitiveType", ""),
            att_spec.get("ItemType", ""),
            att_spec.get("PrimitiveItemType", ""),
        )

        spec_type = "{}/{}/{}/{}".format(
            spec.get("Type", ""),
            spec.get("PrimitiveType", ""),
            spec.get("ItemType", ""),
            spec.get("PrimitiveItemType", ""),
        )

        if att_type != spec_type:
            raise ValidationError("Resource \"{}\" has invalid data in property \"{}\". (GetAtt returns wrong data type)".format(resource_name, property_name))

        return

    value_type = get_value_type(value, source)

    if value_type == MAGIC_TYPE:
        return

    if "PrimitiveType" in spec:
        primitive_type = spec["PrimitiveType"]

        if primitive_type != value_type and primitive_type not in value_type:
            fail(primitive_type)

    elif "Type" in spec:
        custom_type = spec["Type"]

        if custom_type == "List":
            pass  # TODO: Deal with lists
        elif custom_type == "Map":
            pass  # TODO: Deal with maps
        else:
            custom_type = "{}.{}".format(source["Resources"][resource_name]["Type"], spec["Type"])

            validate_properties(resource_name, value, SPEC["PropertyTypes"][custom_type]["Properties"], source)

def validate_properties(resource_name, properties, spec, source):
    """
    Compare the specified properties against the supplied spec.
    The entire source must be passed in to ensure that references etc are valid
    """

    # Check required parameters
    required = [key for key, value in spec.items() if value["Required"]]
    missing = [key for key in required if key not in properties]
    if missing:
        raise ValidationError("Resource \"{}\" has missing required properties: {}".format(resource_name, ", ".join(missing)))

    # Check for unexpected parameters
    unexpected = [key for key in properties if key not in spec]
    if unexpected:
        raise ValidationError("Resource \"{}\" has unexpected properties: {}".format(resource_name, ", ".join(sorted(unexpected))))

    # Validate the contents
    for property_name, value in properties.items():
        validate_property(resource_name, property_name, value, spec[property_name], source)

def validate_resource(resource_name, source):
    """
    Confirm that the resource is valid.
    The entire source must be passed in to ensure that references etc are valid
    """

    resource = source["Resources"][resource_name]

    if "Type" not in resource:
        raise ValidationError("Badly formatted resource: {}".format(resource_name))

    if resource["Type"] not in SPEC["ResourceTypes"]:
        raise ValidationError("Resource \"{}\" has invalid type: {}".format(resource_name, resource["Type"]))

    validate_properties(resource_name, resource.get("Properties", {}), SPEC["ResourceTypes"][resource["Type"]]["Properties"], source)

def validate(source):
    """
    Confirm that the source conforms to the cloudformation spec
    """

    if not isinstance(source, dict):
        raise ValidationError("Badly formatted input")

    if "Resources" not in source:
        raise ValidationError("Missing \"Resources\" property")

    for resource_name in source["Resources"].keys():
        validate_resource(resource_name, source)

    return True
