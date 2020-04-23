/* Copyright 2020 The Brave Authors. All rights reserved.
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

#ifndef BRAVE_BROWSER_BRAVE_REWARDS_CHECKOUT_DIALOG_CONTROLLER_H_
#define BRAVE_BROWSER_BRAVE_REWARDS_CHECKOUT_DIALOG_CONTROLLER_H_

#include "base/memory/weak_ptr.h"
#include "base/callback.h"
#include "base/observer_list.h"
#include "base/observer_list_types.h"

namespace brave_rewards {

struct CheckoutDialogParams {
  std::string description;
  double total;
};

// Defines the interface between the opener of the checkout dialog
// and the classes responsible for managing the behavior of the
// checkout dialog.
class CheckoutDialogController :
    public base::SupportsWeakPtr<CheckoutDialogController> {

 public:
  class Observer : public base::CheckedObserver {
   public:
    virtual void OnPaymentAborted() = 0;
    virtual void OnPaymentCompleted() = 0;
  };

  using OnDialogClosedCallback = base::OnceClosure;

  explicit CheckoutDialogController(CheckoutDialogParams params);
  ~CheckoutDialogController();

  CheckoutDialogController(
      const CheckoutDialogController&) = delete;
  CheckoutDialogController& operator=(
      const CheckoutDialogController&) = delete;

  // Notifies the checkout dialog that the payment has been
  // aborted by the initiator.
  void NotifyPaymentAborted();

  // Notifies the checkout dialog that the payment has been
  // confirmed as completed by the initiator.
  void NotifyPaymentCompleted();

  // Sets a callback that will be called when the checkout
  // dialog is closed.
  void SetOnDialogClosedCallback(OnDialogClosedCallback callback);

 private:
  friend class CheckoutDialogMessageHandler;
  friend class CheckoutDialogDelegate;

  // Internal methods for use by checkout dialog classes:
  void AddObserver(Observer* observer);
  void RemoveObserver(Observer* observer);
  void NotifyDialogClosed();
  const CheckoutDialogParams& params() const { return params_; }

  base::ObserverList<Observer> observers_;
  OnDialogClosedCallback closed_callback_;
  CheckoutDialogParams params_;
};

}  // namespace brave_rewards

#endif  // BRAVE_BROWSER_BRAVE_REWARDS_CHECKOUT_DIALOG_CONTROLLER_H_
