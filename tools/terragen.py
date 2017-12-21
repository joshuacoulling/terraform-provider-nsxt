#  Copyright (c) 2017 VMware, Inc. All Rights Reserved.
#  SPDX-License-Identifier: MPL-2.0

import sys
import re

PACKAGE_NAME = "nsxt"
SDK_PACKAGE_NAME = "api"
MANAGER_PACKAGE_NAME = "manager"

IGNORE_ATTRS = ["Links", "Schema", "Self", "Id", "ResourceType", "CreateTime", "CreateUser", "LastModifiedTime", "LastModifiedUser"]
COMPUTED_ATTRS = ["CreateTime", "CreateUser", "LastModifiedTime", "LastModifiedUser", "SystemOwned"]
FORCENEW_ATTRS = ["TransportZoneId"]
# TODO: ServiceBindings
VIP_SCHEMA_ATTRS = ["Tags", "SwitchingProfileIds", "Revision", "AddressBindings", "SystemOwned"]
VIP_GETTER_ATTRS = ["Tags", "SwitchingProfileIds", "AddressBindings"]
VIP_SETTER_ATTRS = VIP_GETTER_ATTRS

TYPE_MAP = {"string": "schema.TypeString",
            "int32": "schema.TypeInt",
            "int64": "schema.TypeInt",
            "bool": "schema.TypeBool"}

TYPECAST_MAP = {"int64": "int", "int32": "int"}

indent = 0


def convert_name(name):
    tmp = re.sub(r'([A-Z])', r'_\1', name).lower()
    return tmp[1:]


def shift():
    global indent
    indent += 1


def unshift():
    global indent
    indent -= 1


def pretty_writeln(f, line):
    for i in range(indent):
        f.write("    ")
    f.write(line)
    f.write("\n")


def write_header(f):
    pretty_writeln(f, "package %s\n" % PACKAGE_NAME)
    pretty_writeln(f, "import(")
    shift()
    pretty_writeln(f, "\"github.com/hashicorp/terraform/helper/schema\"")
    pretty_writeln(f, "%s \"github.com/vmware/go-vmware-nsxt\"" % SDK_PACKAGE_NAME)
    pretty_writeln(f, "\"github.com/vmware/go-vmware-nsxt/%s\"" % MANAGER_PACKAGE_NAME)
    pretty_writeln(f, "\"net/http\"")
    pretty_writeln(f, "\"fmt\"")
    unshift()
    pretty_writeln(f, ")\n")


def write_attr(f, attr):

    if attr['name'] in VIP_SCHEMA_ATTRS:
        pretty_writeln(f, "\"%s\": get%sSchema()," % (convert_name(attr['name']), attr['name']))
        return

    if attr['type'] not in TYPE_MAP:
        print("Skipping attribute %s due to mysterious type %s" % (attr['name'], attr['type']))
        return

    pretty_writeln(f, "\"%s\": &schema.Schema{" % convert_name(attr['name']))
    shift()
    pretty_writeln(f, "Type:        %s," % TYPE_MAP[attr['type']])
    if attr['comment']:
        pretty_writeln(f, "Description: \"%s\"," % attr['comment'])
    pretty_writeln(f, "Optional:    true,")
    if attr['name'] in FORCENEW_ATTRS:
        pretty_writeln(f, "ForceNew:    true,")
    if attr['name'] in COMPUTED_ATTRS:
        pretty_writeln(f, "Computed:    true,")

    unshift()
    pretty_writeln(f, "},")

def write_func_header(f, resource, operation):
    f.write("\n")
    pretty_writeln(f, "func resource%s%s(d *schema.ResourceData, m interface{}) error {" %
            (resource, operation))
    f.write("\n")
    shift()

def write_nsxclient(f):
    pretty_writeln(f, "nsxClient := m.(*%s.APIClient)\n" % SDK_PACKAGE_NAME)


def write_get_id(f):
    pretty_writeln(f, "id := d.Id()")
    pretty_writeln(f, "if id == \"\" {")
    shift()
    pretty_writeln(f, "return fmt.Errorf(\"Error obtaining logical object id\")")
    unshift()
    pretty_writeln(f, "}\n")


def write_error_check(f, resource, operation):
    if operation == "update":
        pretty_writeln(f, "if err != nil || resp.StatusCode == http.StatusNotFound {")
    else:
        pretty_writeln(f, "if err != nil {")

    shift()
    pretty_writeln(f, "return fmt.Errorf(\"Error during %s %s: " % (resource, operation) + '%v", err)')
    unshift()
    pretty_writeln(f, "}\n")

def write_object(f, resource, attrs, is_create=True):
    used_attrs = []
    for attr in attrs:
        if (is_create and attr['name'] == 'Revision') or attr['name'] in COMPUTED_ATTRS:
            # Revision is irrelevant in create
            continue

        used_attrs.append(attr['name'])
        if attr['name'] in VIP_GETTER_ATTRS:
            pretty_writeln(f, "%s := get%sFromSchema(d)" % (
                convert_name(attr['name']), attr['name']))
            continue

        if attr['type'] in TYPECAST_MAP:
            # type casting is needed
            pretty_writeln(f, "%s := %s(d.Get(\"%s\").(%s))" %
                    (convert_name(attr['name']),
                     attr['type'],
                     convert_name(attr['name']),
                     TYPECAST_MAP[attr['type']]))
        else:
            pretty_writeln(f, "%s := d.Get(\"%s\").(%s)" %
                        (convert_name(attr['name']),
                         convert_name(attr['name']),
                         attr['type']))

    pretty_writeln(f, "%s := %s.%s {" % (convert_name(resource), MANAGER_PACKAGE_NAME, resource))
    shift()
    for attr in used_attrs:
        pretty_writeln(f, "%s: %s," % (attr, convert_name(attr)))

    unshift()

    pretty_writeln(f, "}\n")

def write_create_func(f, resource, attrs, api_section):

    lower_resource = convert_name(resource)
    write_func_header(f, resource, "Create")

    write_nsxclient(f)

    write_object(f, resource, attrs)

    pretty_writeln(f, "%s, resp, err := nsxClient.%s.Create%s(nsxClient.Context, %s)" % (
        lower_resource, api_section, resource, lower_resource))

    f.write("\n")
    write_error_check(f, resource, "create")

    pretty_writeln(f, "if resp.StatusCode != http.StatusCreated {")
    shift()
    pretty_writeln(f, "fmt.Printf(\"Unexpected status returned\")")
    pretty_writeln(f, "return nil")
    unshift()
    pretty_writeln(f, "}")


    pretty_writeln(f, "d.SetId(%s.Id)\n" % lower_resource)

    pretty_writeln(f, "return resource%sRead(d, m)" % resource)
    unshift()
    pretty_writeln(f, "}")


def write_read_func(f, resource, attrs, api_section):

    lower_resource = convert_name(resource)
    write_func_header(f, resource, "Read")

    write_nsxclient(f)
    write_get_id(f)

    # For some resources this is GET and for other it is read
    pretty_writeln(f, "//TerraGen TODO - select the right command for this resource, and delete this comment")
    pretty_writeln(f, "%s, resp, err := nsxClient.%s.Get%s(nsxClient.Context, id)" %
            (lower_resource, api_section, resource))
    pretty_writeln(f, "%s, resp, err := nsxClient.%s.Read%s(nsxClient.Context, id)" %
            (lower_resource, api_section, resource))

    pretty_writeln(f, "if resp.StatusCode == http.StatusNotFound {")
    shift()
    pretty_writeln(f, "fmt.Printf(\"%s not found\")" % resource)
    pretty_writeln(f, 'd.SetId("")')
    pretty_writeln(f, "return nil")
    unshift()
    pretty_writeln(f, "}")

    write_error_check(f, resource, "read")

    for attr in attrs:
        if attr['name'] in IGNORE_ATTRS:
            continue

        if attr['name'] in VIP_SETTER_ATTRS:
            pretty_writeln(f, "set%sInSchema(d, %s.%s)" % (
                attr['name'], lower_resource, attr['name']))
            continue

        pretty_writeln(f, "d.Set(\"%s\", %s.%s)" %
                (attr['name'], lower_resource, attr['name']))

    f.write("\n")
    pretty_writeln(f, "return nil")
    unshift()
    pretty_writeln(f, "}")


def write_update_func(f, resource, attrs, api_section):

    lower_resource = convert_name(resource)
    write_func_header(f, resource, "Update")

    write_nsxclient(f)
    write_get_id(f)

    write_object(f, resource, attrs, is_create=False)
    pretty_writeln(f, "%s, resp, err := nsxClient.%s.Update%s(nsxClient.Context, id, %s)" % (
        lower_resource, api_section, resource, lower_resource))

    f.write("\n")
    write_error_check(f, resource, "update")

    pretty_writeln(f, "return resource%sRead(d, m)" % resource)
    unshift()
    pretty_writeln(f, "}")


def write_delete_func(f, resource, attrs, api_section):

    write_func_header(f, resource, "Delete")

    write_nsxclient(f)
    write_get_id(f)

    pretty_writeln(f, "//TerraGen TODO - select the right command for this resource, and delete this comment")
    pretty_writeln(f, "localVarOptionals := make(map[string]interface{})")
    pretty_writeln(f, "resp, err := nsxClient.%s.Delete%s(nsxClient.Context, id, localVarOptionals)" % (
        api_section, resource))
    pretty_writeln(f, "resp, err := nsxClient.%s.Delete%s(nsxClient.Context, id)" % (
        api_section, resource))

    write_error_check(f, resource, "delete")


    pretty_writeln(f, "if resp.StatusCode == http.StatusNotFound {")
    shift()
    pretty_writeln(f, "fmt.Printf(\"%s not found\")" % resource)
    pretty_writeln(f, 'd.SetId("")')
    unshift()
    pretty_writeln(f, "}")

    unshift()
    pretty_writeln(f, "return nil")
    pretty_writeln(f, "}")


def main():

    if len(sys.argv) != 3:
        print("Usage: %s <sdk resource file> <api section>" % sys.argv[0])
        sys.exit()

    print("Building resource from %s" % sys.argv[1])
    api_section = sys.argv[2]

    with open(sys.argv[1], 'r') as f:
        lines = f.readlines()

    resource = None
    resource_started = False
    attr_comment = None
    attrs = []
    for line in lines:
        line = line.strip()
        match = re.match("type (.+?) struct", line)
        if match:
            resource = match.group(1)
            resource_started = True
            continue

        if not resource_started:
            continue

        if line.startswith('//'):
            attr_comment = line[3:]
            # remove dot if exists
            if attr_comment.endswith('.'):
                attr_comment = attr_comment[:-1]
            continue

        match = re.match("(.+?) (.+?) `json:\"(.+?)\"`", line)
        if match:
            attr_name = match.group(1).strip()
            attr_type = match.group(2).strip()
            attr_meta = match.group(3).strip()
            if attr_name not in IGNORE_ATTRS:
                attrs.append({'name': attr_name,
                              'type': attr_type,
                              'meta': attr_meta,
                              'comment': attr_comment})
            attr_comment = None


    print("Resource: %s" % resource)
    resource_lower = convert_name(resource)
    print(resource_lower)

    with open("resource_%s.go" % resource_lower, 'w') as f:
        write_header(f)

        pretty_writeln(f, "func resource%s() *schema.Resource {" % resource)
        shift()
        pretty_writeln(f, "return &schema.Resource{")
        shift()
        for op in ("Create", "Read", "Update", "Delete"):
            pretty_writeln(f, "%s: resource%s%s," % (op, resource, op))

        f.write("\n")
        pretty_writeln(f, "Schema: map[string]*schema.Schema{")
        shift()

        for attr in attrs:
            write_attr(f, attr)

        unshift()
        pretty_writeln(f, "},")
        unshift()
        pretty_writeln(f, "}")
        unshift()
        pretty_writeln(f, "}")

        write_create_func(f, resource, attrs, api_section)
        write_read_func(f, resource, attrs, api_section)
        write_update_func(f, resource, attrs, api_section)
        write_delete_func(f, resource, attrs, api_section)

main()