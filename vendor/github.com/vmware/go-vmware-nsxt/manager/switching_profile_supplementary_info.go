/* Copyright © 2017 VMware, Inc. All Rights Reserved.
   SPDX-License-Identifier: BSD-2-Clause

   Generated by: https://github.com/swagger-api/swagger-codegen.git */

package manager

// Additional information related to switching profiles
type SwitchingProfileSupplementaryInfo struct {

	// Allowed MAC addresses for BPDU filter white list
	BpduFilterAllowedMacs []string `json:"bpdu_filter_allowed_macs,omitempty"`
}
