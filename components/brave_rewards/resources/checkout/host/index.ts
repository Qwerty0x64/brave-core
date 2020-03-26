/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

import { createStateManager } from './stateManager'

import {
  CreditCardDetails,
  WalletInfo,
  WalletState,
  OrderInfo,
  Host,
  HostState
} from '../interfaces'

function parseDialogArgs (): OrderInfo {
  // TODO(zenparsing): Error handling?
  const argString = chrome.getVariableValue('dialogArguments')
  const { orderInfo } = Object(JSON.parse(argString))
  return {
    description: orderInfo.description,
    total: orderInfo.total
  }
}

// User wallet data is collated using data from multiple calls
// to the rewards service. WalletCollator is used to aggregate
// this data and provide a WalletInfo object when all data is
// available.
function createWalletCollator () {
  const needed = new Set(['balance', 'verified', 'status'])

  let walletInfo: WalletInfo = {
    balance: 0,
    state: 'not-created'
  }

  function update (key: string, fn: () => void): WalletInfo | undefined {
    needed.delete(key)
    fn()
    return needed.size === 0 ? walletInfo : undefined
  }

  return {

    setBalance (balance: number) {
      return update('balance', () => {
        walletInfo = { ...walletInfo, balance }
      })
    },

    resetBalance () {
      needed.add('balance')
    },

    setVerified (verified: boolean) {
      return update('verified', () => {
        if (verified) {
          walletInfo = { ...walletInfo, state: 'verified' }
        }
      })
    },

    setState (state: WalletState) {
      return update('status', () => {
        walletInfo = { ...walletInfo, state }
      })
    }

  }
}

function addWebUIListeners (listeners: object) {
  for (const key of Object.keys(listeners)) {
    self.cr.addWebUIListener(key, (event: any) => {
      // TODO(zenparsing): Disable logging in production?
      console.log(key, event)
      listeners[key](event)
    })
  }
}

export function createHost (): Host {
  const stateManager = createStateManager<HostState>({
    orderInfo: parseDialogArgs()
  })

  const walletCollator = createWalletCollator()

  addWebUIListeners({

    walletBalanceUpdated (event: any) {
      const total = event.total as number
      const rates = event.rates as Record<string, number>
      const lastUpdated = new Date().toISOString()

      // TODO(zenparsing): Get lastUpdated from service

      stateManager.update({
        walletInfo: walletCollator.setBalance(total),
        exchangeRateInfo: { rates, lastUpdated }
      })
    },

    anonWalletStatusUpdated (event: any) {
      stateManager.update({
        walletInfo: walletCollator.setState(event.status)
      })
      if (event.status !== 'created') {
        // If a wallet has not been created we won't receive
        // a walletBalanceUpdated event. Update the balance
        // and rate info to default values.
        stateManager.update({
          walletInfo: walletCollator.setBalance(0),
          exchangeRateInfo: {
            rates: {},
            lastUpdated: new Date().toISOString()
          }
        })
      }
    },

    externalWalletUpdated (event: any) {
      stateManager.update({
        walletInfo: walletCollator.setVerified(event.verified)
      })
    },

    rewardsEnabledUpdated (event: any) {
      stateManager.update({
        settings: { rewardsEnabled: event.rewardsEnabled }
      })
    },

    walletInitialized (event: any) {
      walletCollator.resetBalance()
      chrome.send('getWalletBalance')
      chrome.send('getAnonWalletStatus')
    },

    orderCanceled () {
      chrome.send('dialogClose')
    }

  })

  chrome.send('getRewardsEnabled')
  chrome.send('getWalletBalance')
  chrome.send('getAnonWalletStatus')
  chrome.send('getExternalWallet')

  // TODO(zenparsing): Is this required?
  self.i18nTemplate.process(document, self.loadTimeData)

  return {

    getLocaleString (key: string) {
      return self.loadTimeData.getString(key)
    },

    cancelPayment () {
      chrome.send('cancelPayment')
    },

    enableRewards () {
      chrome.send('enableRewards')

      const { walletInfo } = stateManager.state
      const shouldCreate = walletInfo && (
        walletInfo.state === 'created' ||
        walletInfo.state === 'corrupted'
      )

      if (shouldCreate) {
        chrome.send('createWallet')
        stateManager.update({
          walletInfo: walletCollator.setState('creating')
        })
      }
    },

    payWithCreditCard (cardDetails: CreditCardDetails) {
      console.log('payWithCreditCard', cardDetails)
      // TODO(zenparsing): Send update to service
    },

    payWithWallet () {
      console.log('payWithWallet')
      // TODO(zenparsing): Send update to service
    },

    addListener: stateManager.addListener

  }
}
