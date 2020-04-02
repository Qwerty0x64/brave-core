/* Copyright (c) 2020 The Brave Authors. All rights reserved.
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

#include "brave/renderer/brave_content_settings_agent_impl_helper.h"

#define BRAVE_SVG_PATH_ELEMENT_GET_TOTAL_LENGTH         \
  if (!AllowFingerprinting(GetDocument().GetFrame())) { \
    return 0.0f;                                        \
  }

#include "../../../../../../../third_party/blink/renderer/core/svg/svg_path_element.cc"
#undef BRAVE_SVG_PATH_ELEMENT_GET_TOTAL_LENGTH
