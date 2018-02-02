/* Copyright © 2017 VMware, Inc. All Rights Reserved.
   SPDX-License-Identifier: BSD-2-Clause

   Generated by: https://github.com/swagger-api/swagger-codegen.git */

package aaa

// Role
type NsxRole struct {

	// Permissions
	Permissions []string `json:"permissions"`

	// Role name
	Role string `json:"role"`
}