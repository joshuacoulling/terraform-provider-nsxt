/* Copyright © 2018 VMware, Inc. All Rights Reserved.
   SPDX-License-Identifier: MPL-2.0 */

package nsxt

import (
	"fmt"
	"github.com/hashicorp/terraform/helper/resource"
	"github.com/hashicorp/terraform/terraform"
	"github.com/vmware/go-vmware-nsxt"
	"net/http"
	"testing"
)

func TestAccResourceNsxtLbTcpMonitor_basic(t *testing.T) {
	testAccResourceNsxtLbL4MonitorBasic(t, "tcp")
}

func TestAccResourceNsxtLbUdpMonitor_basic(t *testing.T) {
	testAccResourceNsxtLbL4MonitorBasic(t, "udp")
}

func TestAccResourceNsxtLbTcpMonitor_importBasic(t *testing.T) {
	testAccResourceNsxtLbL4MonitorImport(t, "tcp")
}

func TestAccResourceNsxtLbUdpMonitor_importBasic(t *testing.T) {
	testAccResourceNsxtLbL4MonitorImport(t, "udp")
}

func testAccResourceNsxtLbL4MonitorBasic(t *testing.T, protocol string) {
	name := "test-nsx-monitor"
	updatedName := fmt.Sprintf("%s-update", name)
	testResourceName := fmt.Sprintf("nsxt_lb_%s_monitor.test", protocol)
	port := "7887"
	updatedPort := "8778"
	count := "2"
	interval := "9"
	timeout := "12"
	updatedCount := "5"
	send := "Client hello"
	receive := "Server hello"

	resource.Test(t, resource.TestCase{
		PreCheck:  func() { testAccPreCheck(t) },
		Providers: testAccProviders,
		CheckDestroy: func(state *terraform.State) error {
			return testAccNSXLbL4MonitorCheckDestroy(protocol, state, name)
		},
		Steps: []resource.TestStep{
			{
				Config: testAccNSXLbL4MonitorCreateTemplate(protocol, name, count, interval, port, timeout, send, receive),
				Check: resource.ComposeTestCheckFunc(
					testAccNSXLbL4MonitorExists(protocol, name, testResourceName),
					resource.TestCheckResourceAttr(testResourceName, "display_name", name),
					resource.TestCheckResourceAttr(testResourceName, "description", "test description"),
					resource.TestCheckResourceAttr(testResourceName, "fall_count", count),
					resource.TestCheckResourceAttr(testResourceName, "rise_count", count),
					resource.TestCheckResourceAttr(testResourceName, "interval", interval),
					resource.TestCheckResourceAttr(testResourceName, "timeout", timeout),
					resource.TestCheckResourceAttr(testResourceName, "monitor_port", port),
					resource.TestCheckResourceAttr(testResourceName, "send", send),
					resource.TestCheckResourceAttr(testResourceName, "receive", receive),
					resource.TestCheckResourceAttr(testResourceName, "tag.#", "1"),
				),
			},
			{
				Config: testAccNSXLbL4MonitorCreateTemplate(protocol, updatedName, updatedCount, interval, updatedPort, timeout, send, receive),
				Check: resource.ComposeTestCheckFunc(
					testAccNSXLbL4MonitorExists(protocol, updatedName, testResourceName),
					resource.TestCheckResourceAttr(testResourceName, "display_name", updatedName),
					resource.TestCheckResourceAttr(testResourceName, "description", "test description"),
					resource.TestCheckResourceAttr(testResourceName, "fall_count", updatedCount),
					resource.TestCheckResourceAttr(testResourceName, "rise_count", updatedCount),
					resource.TestCheckResourceAttr(testResourceName, "interval", interval),
					resource.TestCheckResourceAttr(testResourceName, "timeout", timeout),
					resource.TestCheckResourceAttr(testResourceName, "monitor_port", updatedPort),
					resource.TestCheckResourceAttr(testResourceName, "send", send),
					resource.TestCheckResourceAttr(testResourceName, "receive", receive),
					resource.TestCheckResourceAttr(testResourceName, "tag.#", "1"),
				),
			},
		},
	})
}

func testAccResourceNsxtLbL4MonitorImport(t *testing.T, protocol string) {
	name := "test-nsx-monitor"
	testResourceName := fmt.Sprintf("nsxt_lb_%s_monitor.test", protocol)
	resource.Test(t, resource.TestCase{
		PreCheck:  func() { testAccPreCheck(t) },
		Providers: testAccProviders,
		CheckDestroy: func(state *terraform.State) error {
			return testAccNSXLbL4MonitorCheckDestroy(protocol, state, name)
		},
		Steps: []resource.TestStep{
			{
				Config: testAccNSXLbL4MonitorCreateTemplateTrivial(protocol, name),
			},
			{
				ResourceName:      testResourceName,
				ImportState:       true,
				ImportStateVerify: true,
			},
		},
	})
}

func testAccNSXLbL4MonitorExists(protocol string, displayName string, resourceName string) resource.TestCheckFunc {
	return func(state *terraform.State) error {

		nsxClient := testAccProvider.Meta().(*nsxt.APIClient)
		rs, ok := state.RootModule().Resources[resourceName]
		if !ok {
			return fmt.Errorf("NSX LB %s monitor resource %s not found in resources", protocol, resourceName)
		}

		resourceID := rs.Primary.ID
		if resourceID == "" {
			return fmt.Errorf("NSX LB %s monitor resource ID not set in resources", protocol)
		}

		monitor, responseCode, err := nsxClient.ServicesApi.ReadLoadBalancerMonitor(nsxClient.Context, resourceID)
		if err != nil {
			return fmt.Errorf("Error while checking if LB %s monitor %s exists", protocol, monitor.DisplayName)
		}

		if responseCode.StatusCode != http.StatusOK {
			return fmt.Errorf("Error while checking if LB %s monitor %s exists. HTTP return code was %d", protocol, resourceID, responseCode.StatusCode)
		}

		if displayName == monitor.DisplayName {
			return nil
		}
		return fmt.Errorf("NSX LB %s monitor %s wasn't found", protocol, displayName)
	}
}

func testAccNSXLbL4MonitorCheckDestroy(protocol string, state *terraform.State, displayName string) error {
	nsxClient := testAccProvider.Meta().(*nsxt.APIClient)
	monitorType := fmt.Sprintf("nsxt_lb_%s_monitor", protocol)
	for _, rs := range state.RootModule().Resources {

		if rs.Type != monitorType {
			continue
		}

		resourceID := rs.Primary.Attributes["id"]
		monitor, responseCode, err := nsxClient.ServicesApi.ReadLoadBalancerMonitor(nsxClient.Context, resourceID)
		if err != nil {
			if responseCode.StatusCode != http.StatusOK {
				return nil
			}
			return fmt.Errorf("Error while retrieving LB %s monitor with ID %s. Error: %v", protocol, resourceID, err)
		}

		if displayName == monitor.DisplayName {
			return fmt.Errorf("NSX LB %s monitor %s still exists", protocol, displayName)
		}
	}
	return nil
}

func testAccNSXLbL4MonitorCreateTemplate(protocol string, name string, count string, interval string, port string, timeout string, send string, receive string) string {
	return fmt.Sprintf(`
resource "nsxt_lb_%s_monitor" "test" {
  description  = "test description"
  display_name = "%s"
  fall_count   = "%s"
  interval     = "%s"
  monitor_port = "%s"
  rise_count   = "%s"
  timeout      = "%s"
  send         = "%s"
  receive      = "%s"
  tag {
    scope = "scope1"
    tag   = "tag1"
  }
}
`, protocol, name, count, interval, port, count, timeout, send, receive)
}

func testAccNSXLbL4MonitorCreateTemplateTrivial(protocol string, name string) string {
	return fmt.Sprintf(`
resource "nsxt_lb_%s_monitor" "test" {
  description = "test description"
  send        = "Client hello"
  receive     = "Server hello"
}
`, protocol)
}
